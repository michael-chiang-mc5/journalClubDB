// show reply form for posts -->
  $(document).ready(function(){
      $("button[id*='reply_']").click(function(){
          var reply_id1_id2 = $(this).attr("id")
          var arr = reply_id1_id2.split('_')
          var id1 = arr[1]
          var id2 = arr[2]
          $("#replybox_"+id1+"_"+id2).show();
      });
  });

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

      // get post pk
      post_pk = $( this ).prev('input').val()


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




// upvote/downvote
  $(document).ready(function(){
      $("form[id*='vote_']").submit(function(event){
          var vote_updown_id1_id2 = $(this).attr("id")
          var arr = vote_updown_id1_id2.split('_')
          var updown = arr[1]
          var id1 = arr[2]
          var id2 = arr[3]
          $("#voteb_"+updown+"_"+id1+"_"+id2).val(updown+"voting");




                    $.ajax({
                      type:"POST",
                      url: url_js, // Todo: turn this into var if moved to ajax.js
                      data: {
                             csrfmiddlewaretoken: csrf_js,  // Todo: turn this into var if moved to ajax.js
                             'updown': updown,
                             'post_pk': id2,
                             },
                     success: function(data){
                       $("#voteb_"+updown+"_"+id1+"_"+id2).val(updown+"voted");

                              }

                    });





          return false;




      });
  });
