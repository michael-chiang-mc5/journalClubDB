// Make social modal show proper title
$(document).ready(function() {
  $(".activate-login-modal-navbar").click(function() {
    $('#login-title').html("Log in with your Facebook, Twitter, or Google account.<br />It only takes seconds!")
  });
  $(".activate-login-modal-post").click(function() {
    $('#login-title').html("You must log in to post comments.  It only takes seconds!")
  });
  $(".activate-login-modal-vote").click(function() {
    $('#login-title').html("You must log in to vote on comments.  It only takes seconds!")
  });
  $(".activate-login-modal-library").click(function() {
    $('#login-title').html("You must log in to add papers to your library.  It only takes seconds!")
  });
});
