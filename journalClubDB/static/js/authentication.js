
// log in
$(document).ready(function() {
  $('#user_banned').hide()
  $('#wrong_id_or_password').hide()

  $("#login_button").click(function() {
    $('#user_banned').hide()
    $('#wrong_id_or_password').hide()

    var f = $( this ).prev('form')
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
             $('#wrong_id_or_password').show()
             return false
           } else {
             $('#user_banned').show()
             return false
           }

         }
    });

  });
});

// log out
$(document).ready(function() {

  $("#logout_button").click(function() {
    $.get(url_logout, {},
        function(data, status){
          location.reload();
        });
  });
});

// register
$(document).ready(function() {
  $('#username_exists').hide()
  $('#passwords_match').hide()

  $("#register_button").click(function() {
    $('#username_exists').hide()
    $('#passwords_match').hide()


    // check if username is blank
    var username = $('#register_username').val();
    if (username == ''){
       alert('please enter username');
       return false;
    }

    // check if passwords match
    var password1 = $('#register_password1').val();
    var password2 = $('#register_password2').val();
    if (password1 != password2){
      $('#passwords_match').show()
       return false;
    }

    // check if username pre-exists TODO: this doesn't exit main function, need to return twice
    $.get(url_is_field_available, { 'username': username },
        function(data, status){
            if(data == "True"){
              return true
            } else {
              $('#username_exists').show()
              return false
            }
    });

    var f = $( this ).prev('form')
    $.ajax({
         type:"POST",
         url: url_register,
         data: f.serialize(),
         success: function(data){
           $('#myModal').modal('hide')
           location.reload();
         }
    });

  });
});
