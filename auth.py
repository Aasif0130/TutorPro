import streamlit as st

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        try:
            expected_password = st.secrets["passwords"]["teacher_password"]
        except (KeyError, FileNotFoundError):
            expected_password = "admin"
            
        if st.session_state["password"] == expected_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show inputs for password.
        st.markdown("<h2 style='text-align: center; color: #1e293b;'>TutorPro Daily Login</h2>", unsafe_allow_html=True)
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.markdown("<h2 style='text-align: center; color: #1e293b;'>TutorPro Daily Login</h2>", unsafe_allow_html=True)
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True
