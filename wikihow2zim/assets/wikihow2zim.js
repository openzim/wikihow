function extend(obj, src) {
    Object.keys(src).forEach(function(key) { obj[key] = src[key]; });
    return obj;
}

var vjs_options = {"techOrder": ["html5", "ogvjs"], "ogvjs": {"base": "assets/vendor/ogvjs"}, "controlBar": {"pictureInPictureToggle":false}};
// mobile safari won't autoplay muted loop webm
if (/(mobile|iphone|ipad).*safari*/i.test(navigator.userAgent)) { vjs_options.controls = true;}
document.querySelectorAll('.video-js').forEach(function(video) {
    var options = extend(vjs_options, {preload: ((video.getAttribute("class") || "").indexOf("youtube") != -1) ? 'none': 'auto'});
    videojs(video, options);
});
