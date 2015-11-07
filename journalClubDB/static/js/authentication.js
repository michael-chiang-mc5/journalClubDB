
$(document).ready(function() {
  $("#modal_item1").click(function() {
    $('.wrong_id_or_password').hide()
    $('.wrong_id_or_password').mouseleave()
    $('#username_exists').hide()
    $('#username_exists').mouseleave()
    $('.passwords_match').hide()
    $(".passwords_match").mouseleave();
    $('#login-title').html("Register or log in.  It only takes seconds!")
    $('#login-title').show()
  });

  $("#comment-modal, #reply-modal").click(function() {
    $('#login-title').html("You must register to post comments.  It only takes seconds!")
    $('#login-title').show()
  });

  $("#upvote-modal, #downvote").click(function() {
    $('#login-title').html("You must register to vote on comments.  It only takes seconds!")
    $('#login-title').show()
  });

});




// log in
$(document).ready(function() {
  $('#user_banned').hide()
  $('.wrong_id_or_password').hide()
  $('.wrong_id_or_password').mouseleave()
  $('#login-title').hide()

  $("#login_form").submit(function(e) {
    // var f = $( this ).prev('form')
    //alert("haha")
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
             $('.wrong_id_or_password').show()
             $(".wrong_id_or_password").mouseenter();
             return false
           } else {
             $('#user_banned').show()
             return false
           }

         }
    });

  });
});


// register
$(document).ready(function() {
  $('#username_exists').hide()
  $('.passwords_match').hide()

  $("#register_form").submit(function(e) {
    // prevent page from reloading and make sure all warnings are hidden
    e.preventDefault();
    $('#username_exists').hide()
    $('#username_exists').mouseleave()
    $('.passwords_match').hide()
    $(".passwords_match").mouseleave();


    // check if passwords match
    var passwords_match = "True"
    var password1 = $('#register_password1').val();
    var password2 = $('#register_password2').val();
    if (password1 != password2){
      passwords_match = "False"
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
    if (passwords_match == "False") {
      $('.passwords_match').show()
      $(".passwords_match").mouseenter();
    }
    if (username_does_not_preexist == "False") {
      $('#username_exists').show()
      $("#username_exists").mouseenter();
    }
    if (passwords_match == "False" || username_does_not_preexist == "False") {
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

$(document).ready(function() {
  $('[data-toggle="popover"]').popover();
  $("#span0").popover({
      title: "000",
      placement: "top",
      trigger: "manual"
  });
  $(document).ready(function(){
      $('[data-toggle="tooltip"]').tooltip();
  });




});
