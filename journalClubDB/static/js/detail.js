
// submit post
$(document).ready(function() {
  $("a.submit").click(function() {
    $( this ).next('form').submit();
    //$("#formData").submit();
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
