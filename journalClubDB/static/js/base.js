
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

  // This resizes images within post-wrapper div
  $('.post-wrapper img').each(function(index) {
    var img = $(this)
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
