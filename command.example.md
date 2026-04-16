获取视频名称和上传日期：
```shell
uvx yt-dlp --cookies ${COOKIE_FILE} \
 --proxy socks5://192.168.2.61:6665 \
 --remote-components ejs:github \
 --print "title,upload_date" \
 <VIDEO_URL>
```

下载视频：
```shell
uvx yt-dlp --proxy socks5://192.168.2.61:6665 \
 --cookies ${COOKIE_FILE} \
 -o "{处理后的文件名}.%(ext)s" \
 -P "temp:/wsx/store/.cache/youtube/" \
 -P "home:/wsx/store/youtube/video/{处理后的文件名}/" \
 --remote-components ejs:github \
 -f 'bv[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv+ba/b' \
 <VIDEO_URL>
```
