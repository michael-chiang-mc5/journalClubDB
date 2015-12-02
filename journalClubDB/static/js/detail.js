

function ChangeUrl(title, url) {
    // THIS FUNCTION REQUIRES A BROWSER THAT SUPPORTS HTML5
    if (typeof (history.pushState) != "undefined") {
        var obj = { Title: title, Url: url };
        history.pushState(obj, obj.Title, obj.Url);
    } else {
        alert("Please use a modern browser that supports HTML5 (like Google Chrome)");
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
//  $( "li[id='pill']" ).click(function(event){
  $( ".thread-switch-button" ).click(function(event){

    //var pill_id = $(this).attr("id")
    //var arr = pill_id.split('_')
    //var id = arr[1]

    // this changes url to reflect new thread without reloading
    var threadnumber = $(this).attr("data-threadnumber")
    ChangeUrl("","../"+threadnumber+"/")

    // this changes social authentication redirect to go to new thread
    $('.social-login-link').each(function(index) {

      var link = $(this)
      var original_href = link.attr('href')
      var arr = original_href.split('/');

      var reconstructed_str = ''
      $.each(arr, function( index, value ) {
        // this is the equivalent of continue if value==''
        if (value == '') {
          return
        }
        // this is the equivalent of break if index exceeds limit
        if (index > arr.length-3 ) {
          return false
        }
        reconstructed_str += '/' + value
      });
      reconstructed_str += '/' + threadnumber + '/'
      link.attr('href',reconstructed_str)
    });


  });



});
