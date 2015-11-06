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
});

// view post history using dropdown
$(document).ready(function() {
  // only show last post/edit and hide all previous
  $( ".comment-all").hide()
  $( ".comment-last").show()

  // dropdown to select which revision to view
  $( "a[id*='action-']" ).click(function(e) {
    var action_pk_counter = $(this).attr("id")
    var arr = action_pk_counter.split('-')
    var pk = arr[1]
    var counter = arr[2]
    $( ".li-dropdown-" + pk).removeClass("active");
    $( ".li-dropdown-"+pk+"-"+counter).addClass("active");
    var time_text = $( ".li-dropdown-"+pk+"-"+counter+ " > a" ).html();
    $( "#comment-time-"+pk).html(time_text)
    $( ".comment-target-all-" + pk).hide()
    $( "#comment-text-" + pk + "-" + counter).show()
  });



});


// submit form following hyperlink of class "hyperlink-submit-form"
$(document).ready(function() {
  $("a.hyperlink-submit-form").click(function() {
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
               //$( me ).next(".vote-count-post").html( data.score )
               $( "#commentscore-pk-"+post_pk ).html( data.score )
           }
      });
    });

  });


    // upvote/downvote with divs
      $(document).ready(function() {
        $( ".vote-down-off " ).click(function() {
          // get post pk
          post_pk = $( this ).prev('input').val()       // get post private key
          var me = this;
          $.ajax({
               type:"POST",
               url: url_downvote,
               data: {
                      csrfmiddlewaretoken: csrf_js,
                      'post_pk': post_pk,
                      },
               success: function(data){
                   //$( me ).prev(".vote-count-post").html( data.score )
                   $( "#commentscore-pk-"+post_pk ).html( data.score )

               }
          });
        });

      });
