// WARNING: POSSIBLE RACE CONDITIONS WHEN USING TEMPLATES

// view post history using dropdown
$(document).ready(function() {
  // hide all other citations when one is clicked.
  $( "a[id*='citation-toggle-']" ).click(function(e) {
    $('.citation-index-all').collapse('hide');
  });
});
