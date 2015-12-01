

function ChangeUrl(title, url) {
    // THIS FUNCTION REQUIRES A BROWSER THAT SUPPORTS HTML5
    if (typeof (history.pushState) != "undefined") {
        var obj = { Title: title, Url: url };
        history.pushState(obj, obj.Title, obj.Url);
    } else {
        alert("Please use a browser that supports HTML5 (like Google Chrome)");
    }
}

function getImageDimensions(width,height) {
  var maxWidth = 100;
  var maxHeight = 100;

  if(width <= maxWidth && height <= maxHeight) {
  	return [width,height];
  } else if  (width>maxWidth && height <= maxHeight) {
    var factor = maxWidth / width;
    return [maxWidth,Math.round(factor * height)];
  } else if(width<=maxWidth && height > maxHeight) {
    var factor = maxHeight / height;
    return [Math.round(factor * width),maxHeight]
  } else { // both width,height greater than maxWidth, maxHeight
    var factor_w = maxWidth / width;
    var factor_h = maxHeight / height;
    if (factor_w < factor_h) {
      return [Math.round(factor_w * width),Math.round(factor_w * height)];
    } else {
      return [Math.round(factor_h * width),Math.round(factor_h * height)];
    }
  }
}

$(document).ready(function() {

  if(window.location.hash) {
    var url = window.location.href
    var focused_div = url.substring(url.indexOf("#")+1)
    $('#'+focused_div).addClass("background-color-yellow")
  }

  // Change url when different tabs
  $( "li[id*='pill_']" ).click(function(event){
    var pill_id = $(this).attr("id")
    var arr = pill_id.split('_')
    var id = arr[1]
    ChangeUrl("","../"+id+"/")
  });

  $('.post-wrapper img').each(function(index) {
    var img = $(this)
    img.hide()
    $(img).load(function(){
      var width = img.width()
      var height = img.height()
      var resized_width_height = getImageDimensions(width,height);
      img.width(resized_width_height[0])
      img.height(resized_width_height[1])
      img.wrap( "<a href='" + img.attr("src") + "'></a>" );
      img.show()
    });
  });

});
