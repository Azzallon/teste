# yolov3

## Input

![Input](input.jpg)

(Image from https://pixabay.com/ja/photos/%E3%83%AD%E3%83%B3%E3%83%89%E3%83%B3%E5%B8%82-%E9%8A%80%E8%A1%8C-%E3%83%AD%E3%83%B3%E3%83%89%E3%83%B3-4481399/)

Shape : (1, 3, 416, 416)  
Range : [0.0, 1.0]

## Output

![Output](output.png)

- category : [0,79]  
- probablity : [0.0,1.0]  
- position : x, y, w, h [0,1]  

### usage
Automatically downloads the onnx and prototxt files on the first run.
It is necessary to be connected to the Internet while downloading.

For the sample image,
``` bash
$ python3 yolov3.py
```

If you want to specify the input image, put the image path after the `--input` option.  
You can use `--savepath` option to change the name of the output file to save.
```bash
$ python3 yolov3.py --input IMAGE_PATH --savepath SAVE_IMAGE_PATH
```

By adding the `--video` option, you can input the video.   
If you pass `0` as an argument to VIDEO_PATH, you can use the webcam input instead of the video file.
```bash
$ python3 yolov3.py --video VIDEO_PATH
```

## Reference

- [ONNX Model Zoo](https://github.com/onnx/models/tree/master/vision/object_detection_segmentation/yolov3)

## Framework

ONNX Runtime

## Model Format

ONNX opset=10

## Netron

[yolov3.opt2.onnx.prototxt](https://netron.app/?url=https://storage.googleapis.com/ailia-models/yolov3/yolov3.opt2.onnx.prototxt)
