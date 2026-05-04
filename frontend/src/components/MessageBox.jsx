function MessageBox({ type = "info", title, message }) {
  return (
    <div className={`message-box ${type}`}>
      <strong>{title}</strong>
      <p>{message}</p>
    </div>
  );
}

export default MessageBox;