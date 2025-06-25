function validateForm() {
    var password = document.forms[0]["password"].value;
    var regex = /^(?=.*[A-Z])(?=.*\W).{6,}$/; // at least 6 chars, one capital, one symbol
    if (!regex.test(password)) {
        alert("Password must be at least 6 characters long, contain an uppercase letter and a symbol.");
        return false;
    }
    return true;
}
