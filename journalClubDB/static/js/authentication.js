
// Make login modal show title and clear error messages
$(document).ready(function() {
  $('.username_error_message').hide()
  $('.username_error_message').mouseleave()
  $('.password_error_message').hide()
  $(".password_error_message").mouseleave();

  $('.login_error_message').hide()
  $(".login_error_message").mouseleave();

  $(".activate-login-modal-navbar").click(function() {
    $('#login-title').html("Register or log in.  It only takes seconds!")
  });
  $(".activate-login-modal-post").click(function() {
    $('#login-title').html("You must register to post comments.  It only takes seconds!")
  });
  $(".activate-login-modal-vote").click(function() {
    $('#login-title').html("You must register to vote on comments.  It only takes seconds!")
  });
  $(".activate-login-modal-library").click(function() {
    $('#login-title').html("You must register to add papers to your library.  It only takes seconds!")
  });
});

// submit login form
$(document).ready(function() {
  $("#login_form").submit(function(e) {
    e.preventDefault();
    var me = $( this )
    var url = me.attr('href')
    var origin = window.location.pathname;
    $.ajax({
         type:"POST",
         url: url,
         data: me.serialize(),
         success: function(data){
           if(data == "login_successful"){
             $('#social-auth-modal').modal('hide')

             if (origin.substring(0, 7) == "/reset/" || origin.substring(0, 16) == "/password_reset/" ) {
               window.location.href = "/papers/";
               return true
             } else {
               location.reload();
               return true
             }
           } else if (data == "login_unsuccessful") {
             $(".login_error_message").attr('data-original-title', "wrong username or password")
             $('.login_error_message').show()
             $(".login_error_message").mouseenter();
             return false
           } else {
             $(".login_error_message").attr('data-original-title', "account banned")
             $('.login_error_message').show()
             $(".login_error_message").mouseenter();
             return false
           }
         }
    });
  });
});

// submit new user registration form
$(document).ready(function() {
  $("#register_form").submit(function(e) {
    e.preventDefault();

    $('.username_error_message').hide()
    $('.username_error_message').mouseleave()
    $('.password_error_message').hide()
    $('.password_error_message').mouseleave()

    // submit registration form
    var me = $( this )
    var url = me.attr('href')
    $.ajax({
         type:"POST",
         url: url,
         data: me.serialize(),
         success: function(data){
           var block_modal_closing = false;
           // check for problems with username
           if (!data.username_unique) {
             $(".username_error_message").attr('data-original-title', "username already exists, please pick a different one")
             $(".username_error_message").show();
             $(".username_error_message").mouseenter();
             block_modal_closing = true;
           } else if (!data.username_long_enough) {
             $(".username_error_message").attr('data-original-title', "username must be at least six characters long")
             $(".username_error_message").show();
             $(".username_error_message").mouseenter();
             block_modal_closing = true;
           } else if (!data.username_no_crazy_characters) {
             $(".username_error_message").attr('data-original-title', "username can only contain alphanumeric characters, underscores, and dashes")
             $(".username_error_message").show();
             $(".username_error_message").mouseenter();
             block_modal_closing = true;
           }
           // check for problems with password
           if (!data.passwords_match) {
             $(".password_error_message").attr('data-original-title', "passwords do not match, please re-type passwords")
             $(".password_error_message").show();
             $(".password_error_message").mouseenter();
             block_modal_closing = true;
           } else if (!data.password_long_enough) {
             $(".password_error_message").attr('data-original-title', "password must be at least six characters long")
             $(".password_error_message").show();
             $(".password_error_message").mouseenter();
             block_modal_closing = true;
           }


           if (block_modal_closing) {
             return false;
           }

          $('#social-auth-modal').modal('hide')
          location.reload();
         }
    });

  });
});

// Bootstrap tooltips must be initialized with jQuery
$(document).ready(function(){
    $('[data-toggle="tooltip"]').tooltip();
});
