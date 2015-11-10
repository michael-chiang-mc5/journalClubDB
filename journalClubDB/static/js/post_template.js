$(document).ready(function() {

  // this implements upvote functionality
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
             $( me ).addClass('upvoted-arrow').removeClass('up-arrow');
             $( "#down-"+post_pk ).addClass('down-arrow').removeClass('downvoted-arrow');
             $( "#commentscore-pk-"+post_pk ).html( data.score )
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
             $( me ).addClass('up-arrow').removeClass('upvoted-arrow');
             $( "#commentscore-pk-"+post_pk ).html( data.score )
           }
      });
    }
  });

  // this implements downvote functionality
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
             $( me ).addClass('downvoted-arrow').removeClass('down-arrow');
             $( "#up-"+post_pk ).addClass('up-arrow').removeClass('upvoted-arrow');
             $( "#commentscore-pk-"+post_pk ).html( data.score )
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
             $( me ).addClass('down-arrow').removeClass('downvoted-arrow');
             $( "#commentscore-pk-"+post_pk ).html( data.score )
           }
      });
    }
  });

  // this implements history button functionality
  $( ".comment-all").hide()   // only show last post/edit and hide all previous
  $( ".comment-last").show()
  $( "a[id*='action-']" ).click(function(e) {   // dropdown to select which revision to view
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
