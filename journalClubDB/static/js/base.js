$(document).ready(function() {

  // this implements reply and edit button functionality
  $("a.hyperlink-submit-form").click(function() {
    $( this ).next('form').submit();
  });

});
