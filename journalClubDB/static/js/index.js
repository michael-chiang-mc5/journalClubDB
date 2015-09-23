

// view post history using dropdown
$(document).ready(function() {
  // dropdown to select which revision to view
  $( "a[id*='citation-toggle-']" ).click(function(e) {
    var citation_toggle_counter = $(this).attr("id")
    var arr = citation_toggle_counter.split('-')
    var counter = arr[2]
    // $( ".citation-index-all").removeClass("in");
    $('.citation-index-all').collapse('hide');
  });
});
