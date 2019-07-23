# Isee
3rd yoosee camera solution

## Capturing

Installing ffmpeg to capture RTSP stream
```
ffmpeg -i rtsp://admin:password@192.168.0.7:554/onvif1 -codec copy -map 0 -f segment -strftime 1 -segment_time 300 -segment_format mpeg2 Monitor/out%Y-%m-%d_%H-%M-%S.ts
```

## Cleaning old files when storage is full

## Upload file to cloud storage

## Web page to watch camera records
