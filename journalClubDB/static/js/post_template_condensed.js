// WARNING: POSSIBLE RACE CONDITIONS WHEN USING TEMPLATES

$(document).ready(function() {

  // This keeps dropdown menu from closing on click
  $('.dropdown-menu').click(function(event){
       event.stopPropagation();
   });


  // Upvote, downvote functionality is placed in base.js in order to prevent race conditions

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

  // this implements delete post functionality
  $('.delete-post-are-you-sure').hide()
  $('.delete-post-confirmation').hide()
  $('.delete-post-button').click(function(e) {
    $(this).hide()
    $(this).next('.delete-post-are-you-sure').show()
  });
  $('.delete-post-no').click(function(e) {
    $(this).parent().prev('.delete-post-button').show()
    $(this).parent('.delete-post-are-you-sure').hide()
  });
  $(".delete-post-yes").click(function() {
    f = $(this).next('form');
    var url = f.attr( 'action' );
    $.ajax({
      type: "POST",
      url: url,
      data: f.serialize(),
      success: function(data) { // update post to be deleted
        f.parent('.delete-post-are-you-sure').hide()
        f.parent('.delete-post-are-you-sure').next('.delete-post-confirmation').show()
      }
    });
  });

});
