function ChangeUrl(title, url) {
    if (typeof (history.pushState) != "undefined") {
        var obj = { Title: title, Url: url };
        history.pushState(obj, obj.Title, obj.Url);
    } else {
        //alert("Browser does not support HTML5.");
    }
}

$(document).ready(function() {
  $( "li[id*='pill_']" ).click(function(event){
    var pill_id = $(this).attr("id")
    var arr = pill_id.split('_')
    var id = arr[1]
    ChangeUrl("","../"+id+"/")
  });
  //$("#pill_2").click(function() {
  //  ChangeUrl("","../asdf.html")
  //});
});



// bring up postForm.html
$(document).ready(function() {
  $("a.submit").click(function() {
    $( this ).next('form').submit();
  });
});

// upvote/downvote with divs
  $(document).ready(function() {
    $( ".vote-up-off " ).click(function() {
      post_pk = $( this ).prev('input').val()       // get post private key
      var me = this;
      $.ajax({
           type:"POST",
           url: url_upvote,
           data: {
                  csrfmiddlewaretoken: csrf_js,
                  'post_pk': post_pk,
                  },
           success: function(data){
               $( me ).next(".vote-count-post").html( data.score )
           }
      });
    });

  });


    // upvote/downvote with divs
      $(document).ready(function() {
        $( ".vote-down-off " ).click(function() {
          // get post pk
          post_pk = $( this ).prevAll('input').val()
          var me = this;
          $.ajax({
               type:"POST",
               url: url_downvote,
               data: {
                      csrfmiddlewaretoken: csrf_js,
                      'post_pk': post_pk,
                      },
               success: function(data){
                   $( me ).prev(".vote-count-post").html( data.score )
               }
          });
        });

      });
