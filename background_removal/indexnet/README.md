# Indexnet

### input

input image
![input_image](input.jpg)

input trimap
![input_trimap](trimap.png)

(from https://github.com/open-mmlab/mmediting/tree/master/tests/data/merged and https://github.com/open-mmlab/mmediting/tree/master/tests/data/trimap)

Ailia input shape: (1, 4, 576, 800) input range: (0,1) input color order : RGBA(torch)

### output
![output_image](output.png)

### usage
Automatically downloads the onnx and prototxt files on the first run.
It is necessary to be connected to the Internet while downloading.

For the sample image,
``` bash
$ python3 indexnet.py
```

If you want to specify the input image, put the image path after the `--input` and `--trimap` option.  
You can use `--savepath` option to change the name of the output file to save.
```bash
$ python3 indexnet.py --input IMAGE_PATH --trimap TRIMAP_PATH --savepath SAVE_IMAGE_PATH
```

If you do not have a trimap image for your input image, you can use the `-a u2net` option, while not setting the `--trimap` option. It will automatically use the [U^2-Net](https://github.com/axinc-ai/ailia-models/tree/master/image_segmentation/u2net) model to compute a trimap of your input image.
```bash
$ python3 indexnet.py --input IMAGE_PATH --savepath SAVE_IMAGE_PATH -a u2net
```

You can use onnxRuntime for inference with `-n` option.
```bash
$ python3 indexnet.py -n
```

By adding the `--video` option, you can input the video.   
If you pass `0` as an argument to VIDEO_PATH, you can use the webcam input instead of the video file. The trimap is generated by U^2-Net.
```bash
$ python3 indexnet.py --video VIDEO_PATH
```

### Reference

[Indices Matter: Learning to Index for Deep Image Matting](https://github.com/open-mmlab/mmediting/tree/master/configs/mattors/indexnet)

### Framework
Pytorch 1.3.0


### Model Format
ONNX opset = 11


### Netron
[indexnet.onnx.prototxt](https://netron.app/?url=https://storage.googleapis.com/ailia-models/indexnet/indexnet.onnx.prototxt)

