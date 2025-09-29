# donde construyes el dict por firma:
st = getattr(s, "signing_time", None)
signing_time = st.isoformat() if st else None

data = {
    # ...
    "signing_time": signing_time,
    # ...
}
