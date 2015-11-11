
// Make login modal pop up and clear error messages
$(document).ready(function() {
  $( "[class^='activate-login-modal-'] " ).click(function() {
    $('#username_exists').hide()
    $('#username_exists').mouseleave()
    $('.passwords_match_login').hide()
    $(".passwords_match_login").mouseleave();
    $('.passwords_match_register').hide()
    $(".passwords_match_register").mouseleave();
    $('#user_banned').hide()
    $('#user_banned').mouseleave();
  });
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
    var f = $( this )
    $.ajax({
         type:"POST",
         url: url_login,
         data: f.serialize(),
         success: function(data){
           if(data == "True"){
             $('#myModal').modal('hide')
             location.reload();
             return true
           } else if (data == "False") {
             $('.passwords_match_login').show()
             $(".passwords_match_login").mouseenter();
             return false
           } else {
             $('#user_banned').show()
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

    // check if passwords match
    var passwords_match_register = "True"
    var password1 = $('#register_password1').val();
    var password2 = $('#register_password2').val();
    if (password1 != password2){
      passwords_match_register = "False"
    }

    // check if username pre-exists
    var username = $('#register_username').val();
    var username_does_not_preexist = "True"
    $.ajax({
        url : url_is_field_available,
        data : { 'username': username },
        type : "get",
        async: false,
        success : function(data) {
          if (data == "False" ) {
            username_does_not_preexist = "False"
          }
        }
     });

   // form check
    if (passwords_match_register == "False") {
      $('.passwords_match_register').show()
      $(".passwords_match_register").mouseenter();
    }
    if (username_does_not_preexist == "False") {
      $('#username_exists').show()
      $("#username_exists").mouseenter();
    }
    if (passwords_match_register == "False" || username_does_not_preexist == "False") {
      return false
    }

    // submit registration form
    var me = $( this )
    $.ajax({
         type:"POST",
         url: url_register,
         data: me.serialize(),
         success: function(data){
           $('#myModal').modal('hide')
           location.reload();
         }
    });

  });
});

// Bootstrap tooltips must be initialized with jQuery
$(document).ready(function(){
    $('[data-toggle="tooltip"]').tooltip();
});
