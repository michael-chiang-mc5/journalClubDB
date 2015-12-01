

function ChangeUrl(title, url) {
    // THIS FUNCTION REQUIRES A BROWSER THAT SUPPORTS HTML5
    if (typeof (history.pushState) != "undefined") {
        var obj = { Title: title, Url: url };
        history.pushState(obj, obj.Title, obj.Url);
    } else {
        alert("Please use a browser that supports HTML5 (like Google Chrome)");
    }
}


$(document).ready(function() {



  // Highlight url target
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



});
