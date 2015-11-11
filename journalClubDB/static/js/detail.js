

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

  // Change url when different tabs
  $( "li[id*='pill_']" ).click(function(event){
    var pill_id = $(this).attr("id")
    var arr = pill_id.split('_')
    var id = arr[1]
    ChangeUrl("","../"+id+"/")
  });
});
