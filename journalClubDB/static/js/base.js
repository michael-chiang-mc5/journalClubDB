$(document).ready(function() {


    // this implements upvote functionality. It would be most readable to place this in post_template.js, but multiple scripts will cause race collisions.
    $( "a[id^='up-'] " ).click(function() {
      post_pk = $( this ).prev('input').val()       // get post private key
      var me = this;
      if ( $( me ).hasClass('up-arrow') )  {
        $.ajax({
             type:"POST",
             url: url_upvote,
             data: {
                    csrfmiddlewaretoken: csrf_js,
                    'post_pk': post_pk,
                    },
             success: function(data){
               $( me ).addClass('upvoted-arrow').removeClass('up-arrow').addClass('active-vote');
               $( "#down-"+post_pk ).addClass('down-arrow').removeClass('downvoted-arrow').removeClass('active-vote');
               $( "#commentscore-pk-"+post_pk ).html( data.score )
               $( "#up-"+post_pk ).html( 'upvoted' )
               $( "#down-"+post_pk ).html( 'downvote' )                              
             }
        });
      } else if ( $( me ).hasClass('upvoted-arrow') ) {
        $.ajax({
             type:"POST",
             url: url_upvote,
             data: {
                    csrfmiddlewaretoken: csrf_js,
                    'post_pk': post_pk,
                    },
             success: function(data){
               $( me ).addClass('up-arrow').removeClass('upvoted-arrow').removeClass('active-vote');
               $( "#commentscore-pk-"+post_pk ).html( data.score )
               $( "#up-"+post_pk ).html( 'upvote' )
             }
        });
      }
    });

    // this implements downvote functionality. It would be most readable to place this in post_template.js, but multiple scripts will cause race collisions.
    $( "a[id^='down-'] " ).click(function() {
      post_pk = $( this ).prev('input').val()       // get post private key
      var me = this;
      if ( $( me ).hasClass('down-arrow') )  {
        $.ajax({
             type:"POST",
             url: url_downvote,
             data: {
                    csrfmiddlewaretoken: csrf_js,
                    'post_pk': post_pk,
                    },
             success: function(data){
               $( me ).addClass('downvoted-arrow').removeClass('down-arrow').addClass('active-vote');;
               $( "#up-"+post_pk ).addClass('up-arrow').removeClass('upvoted-arrow').removeClass('active-vote');;
               $( "#commentscore-pk-"+post_pk ).html( data.score )
               $( "#down-"+post_pk ).html( 'downvoted' )
               $( "#up-"+post_pk ).html( 'upvote' )
             }
        });
      } else if ( $( me ).hasClass('downvoted-arrow') ) {
        $.ajax({
             type:"POST",
             url: url_downvote,
             data: {
                    csrfmiddlewaretoken: csrf_js,
                    'post_pk': post_pk,
                    },
             success: function(data){
               $( me ).addClass('down-arrow').removeClass('downvoted-arrow').removeClass('active-vote');;
               $( "#commentscore-pk-"+post_pk ).html( data.score )
               $( "#down-"+post_pk ).html( 'downvote' )
             }
        });
      }
    });


  // this implements functionality to submit succeeding form with hyperlink is clicked
  $("a.hyperlink-submit-form").click(function() {
    $( this ).next('form').submit();
  });

});
