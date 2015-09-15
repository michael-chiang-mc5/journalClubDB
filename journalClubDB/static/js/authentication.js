
// log in
$(document).ready(function() {

  $("#login_button").click(function() {
    alert("asdfsdf")
    var f = $( this ).prev('form')
    $.ajax({
         type:"POST",
         url: url_login,
         data: f.serialize(),
         success: function(data){
           $('#myModal').modal('hide')
         }
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
    $.get('/papers/is_field_available/', { 'username': username },
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
         }
    });

  });
});
