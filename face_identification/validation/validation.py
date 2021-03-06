import sys
import os
import re

import numpy as np
import cv2
import matplotlib.pyplot as plt

import ailia

# import original modules
sys.path.append('../../util')
from utils import get_base_parser, update_parser  # noqa: E402
from image_utils import load_image  # noqa: E402
from model_utils import check_and_download_models  # noqa: E402


# ======================
# PARAMETERS
# ======================
MODEL_LISTS = [
    'arcface', 'vggface2',
    'arcface_mixed_90_82', 'arcface_mixed_90_99', 'arcface_mixed_eq_90_89'
]

# the threshold was calculated by the `test_performance` function in `test.py`
# of the original repository
THRESHOLD = 0.25572845
THRESHOLDS = [i / 100 for i in range(0, 50, 1)]

# ======================
# Arguemnt Parser Config
# ======================
parser = get_base_parser(
    'Determine if the person is the same from two facial images.',
    None,
    None,
)
# overwrite default arguments
parser.add_argument(
    '-i', '--input', metavar='INPUT FOLDER',
    default=None,
    help='The input folder path. ' +
         'Create confusion matrix.'
)
parser.add_argument(
    '-a', '--arch', metavar='ARCH',
    default='arcface', choices=MODEL_LISTS,
    help='model lists: ' + ' | '.join(MODEL_LISTS)
)
parser.add_argument(
    '-s', '--skip',
    action='store_true',
    help='RCalculate using only some images'
)
args = update_parser(parser)

if args.arch == "vggface2":
    WEIGHT_PATH = 'resnet50_scratch.caffemodel'
    MODEL_PATH = 'resnet50_scratch.prototxt'
    REMOTE_PATH = "https://storage.googleapis.com/ailia-models/vggface2/"
    IMAGE_HEIGHT = 224
    IMAGE_WIDTH = 224
else:
    WEIGHT_PATH = args.arch+'.onnx'
    MODEL_PATH = args.arch+'.onnx.prototxt'
    REMOTE_PATH = "https://storage.googleapis.com/ailia-models/arcface/"
    IMAGE_HEIGHT = 128
    IMAGE_WIDTH = 128


# ======================
# Utils
# ======================
def preprocess_image_arcface(image, input_is_bgr=False):
    # (ref: https://github.com/ronghuaiyang/arcface-pytorch/issues/14)
    # use origin image and fliped image to infer,
    # and concat the feature as the final feature of the origin image.
    if input_is_bgr:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if "eq_" in args.arch:
        image = cv2.equalizeHist(image)
    image = np.dstack((image, np.fliplr(image)))
    image = image.transpose((2, 0, 1))
    image = image[:, np.newaxis, :, :]
    image = image.astype(np.float32, copy=False)
    return image / 127.5 - 1.0  # normalize


def preprocess_image_vggface2(img, input_is_bgr=False):
    if input_is_bgr:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # normalize image
    MEAN = np.array([131.0912, 103.8827, 91.4953])  # to normalize input image
    input_data = (img.astype(np.float) - MEAN)
    input_data = input_data.transpose((2, 0, 1))
    input_data = input_data[np.newaxis, :, :, :]
    return input_data


def prepare_input_data(image_path):
    if args.arch == "vggface2":
        image = load_image(
            image_path,
            (IMAGE_HEIGHT, IMAGE_WIDTH),
            normalize_type='None',
            gen_input_ailia=False
        )
        return preprocess_image_vggface2(image)
    else:
        # arcface
        image = load_image(
            image_path,
            image_shape=(IMAGE_HEIGHT, IMAGE_WIDTH),
            rgb=False,
            normalize_type='None'
        )
        return preprocess_image_arcface(image)


def cosin_metric(x1, x2):
    return np.dot(x1, x2) / (np.linalg.norm(x1) * np.linalg.norm(x2))


def l2_metric(feature1, feature2):
    norm1 = np.sqrt(np.sum(np.abs(feature1**2)))
    norm2 = np.sqrt(np.sum(np.abs(feature2**2)))
    dist = feature1/norm1-feature2/norm2
    l2_norm = np.sqrt(np.sum(np.abs(dist**2)))
    return l2_norm


def get_evaluation_files(input):
    folder_cnt = 0

    file_dict = {}
    file_list = []

    for src_dir, dirs, files in os.walk(input):
        # files = sorted(files)
        files = sorted(files, key=lambda var: [
            int(x) if x.isdigit() else x
            for x in re.findall(r'[^0-9]|[0-9]+', var)
        ])
        for file_ in files:
            root, ext = os.path.splitext(file_)

            if file_ == ".DS_Store":
                continue
            if file_ == "Thumbs.db":
                continue
            if not(ext == ".jpg" or ext == ".png" or ext == ".bmp"):
                continue

            folders = src_dir.split("/")
            folder = folders[len(folders)-1]
            if not(folder in file_dict):
                file_dict[folder] = []
                folder_cnt = folder_cnt+1
            if args.skip:
                NUM_SKIP_PER_PERSON = 4
                if(len(file_dict[folder]) >= NUM_SKIP_PER_PERSON):
                    continue
                NUM_SKIP_PERSON = 16
                if folder_cnt >= NUM_SKIP_PERSON:
                    continue
            file_dict[folder].append(src_dir+"/"+file_)
            file_list.append(src_dir+"/"+file_)

    return file_list


def get_feature_values(net, file_list):
    BATCH_SIZE = net.get_input_shape()[0]
    fe_list = []
    for i in range(0, len(file_list)):
        inputs0 = file_list[i]
        print("feature extracting "+inputs0)
        imgs_1 = prepare_input_data(inputs0)
        if BATCH_SIZE == 4:
            imgs_1 = np.concatenate([imgs_1, imgs_1], axis=0)
        preds_ailia1 = net.predict(imgs_1)
        if args.arch == "vggface2":
            fe_1 = preds_ailia1[0]
        else:
            fe_1 = np.concatenate([preds_ailia1[0], preds_ailia1[1]], axis=0)
        fe_list.append(fe_1)
    return fe_list


def compute_similality(heatmap, expect, file_list, fe_list, face_count):
    for i0 in range(0, face_count):
        for i1 in range(0, face_count):
            inputs0 = file_list[i0]
            inputs1 = file_list[i1]

            # postprocessing
            fe_1 = fe_list[i0]
            fe_2 = fe_list[i1]
            if args.arch == "vggface2":
                sim = 1.0 - l2_metric(fe_1, fe_2)
            else:
                sim = cosin_metric(fe_1, fe_2)

            ex = 0
            f0 = inputs0.split("/")
            f1 = inputs1.split("/")

            f0 = f0[len(f0)-2]
            f1 = f1[len(f1)-2]

            if f0 == f1:
                ex = 1

            print(f'Similarity of ({inputs0}, {inputs1}) : {sim:.3f}')
            # if THRESHOLD > sim:
            #     print('They are not the same face!')
            # else:
            #     print('They are the same face!')

            heatmap[i0, i1] = sim
            expect[i0, i1] = ex
    return heatmap, expect


def decide_threshold(heatmap, expect, face_count):
    best_threshold = 0.0
    best_accuracy = 0.0
    for threshold in THRESHOLDS:
        success = 0
        failed = 0

        for i0 in range(0, face_count):
            for i1 in range(0, face_count):
                sim = heatmap[i0, i1]
                ex = expect[i0, i1]

                if (ex == 1 and threshold <= sim) or \
                   (ex == 0 and threshold > sim):
                    success = success + 1
                else:
                    failed = failed + 1

        accuracy = int(success * 10000 / (success + failed))/100
        print("threshold "+str(threshold)+" accuracy "+str(accuracy))
        if best_accuracy < accuracy:
            best_accuracy = accuracy
            best_threshold = threshold

    return best_threshold, best_accuracy


def compute_final_result(
        detected, heatmap, expect, face_count, best_threshold
):
    for i0 in range(0, face_count):
        for i1 in range(0, face_count):
            sim = heatmap[i0, i1]

            if best_threshold <= sim:
                detected[int(i0), int(i1)] = 1
            else:
                detected[int(i0), int(i1)] = 0


def display_result(file_list, fe_list):
    fig = plt.figure(figsize=(12.0, 12.0))

    ax1 = fig.add_subplot(2, 2, 1)
    ax2 = fig.add_subplot(2, 2, 2)
    ax3 = fig.add_subplot(2, 2, 4)

    ax1.tick_params(labelbottom="on")
    ax2.tick_params(labelleft="on")
    ax3.tick_params(labelleft="on")

    max_cnt = len(file_list)

    x = np.zeros((max_cnt))
    y = np.zeros((max_cnt))

    heatmap = np.zeros((len(file_list), len(file_list)))
    expect = np.zeros((len(file_list), len(file_list)))
    detected = np.zeros((len(file_list), len(file_list)))

    face_count = len(file_list)

    compute_similality(heatmap, expect, file_list, fe_list, face_count)
    best_threshold, best_accuracy = decide_threshold(
        heatmap, expect, face_count)
    compute_final_result(detected, heatmap, expect, face_count, best_threshold)

    print("best threshold "+str(best_threshold) +
          " best accuracy "+str(best_accuracy))

    ax1.pcolor(expect, cmap=plt.cm.Blues)
    ax2.pcolor(detected, cmap=plt.cm.Blues)
    ax3.pcolor(heatmap, cmap=plt.cm.Blues)

    if False:   # Plot values
        for y in range(heatmap.shape[0]):
            for x in range(heatmap.shape[1]):
                if heatmap[y, x] != 0:
                    ax2.text(
                        x + 0.5, y + 0.5, str(heatmap[y, x]),
                        horizontalalignment='center',
                        verticalalignment='center',
                        fontsize=8,
                    )

    ax1.set_title('expected ')
    ax1.set_xlabel('(face2)')
    ax1.set_ylabel('(face1)')
    ax1.legend(loc='upper right')

    ax2.set_title('detected (threshold '+str(best_threshold) +
                  ' accuracy '+str(best_accuracy)+' %)')
    ax2.set_xlabel('(face2)')
    ax2.set_ylabel('(face1')
    ax2.legend(loc='upper right')

    ax3.set_title('similality')
    ax3.set_xlabel('(face2)')
    ax3.set_ylabel('(face1')
    ax3.legend(loc='upper right')

    fig.savefig("confusion_"+args.arch+".png", dpi=100)

    print('Script finished successfully.')


# ======================
# Main functions
# ======================
def main():
    # model files check and download
    check_and_download_models(WEIGHT_PATH, MODEL_PATH, REMOTE_PATH)

    # check folder
    if args.input is None or not os.path.exists(args.input):
        print("Input folder not found")
        return

    # get target files
    file_list = get_evaluation_files(args.input)

    # net initialize
    net = ailia.Net(MODEL_PATH, WEIGHT_PATH, env_id=args.env_id)

    # get feature values
    fe_list = get_feature_values(net, file_list)

    # create confusion matrix
    display_result(file_list, fe_list)


if __name__ == "__main__":
    main()
