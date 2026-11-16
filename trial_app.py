import streamlit as st

st.title("My First AI Application")

st.write("Welcome to my NatWest AI preparation!")

name = st.text_input("Enter your name")

if name:
    st.success(f"Hello {name}! Your application is working.")

st.subheader("Expense Calculator")

amount = st.number_input(
    "Enter your expense amount",
    min_value=0.0
)

if st.button("Calculate"):
    st.write(f"Your expense is ₹{amount:,.2f}")