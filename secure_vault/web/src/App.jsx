import { useState } from "react";
import { apiGet, apiPost } from "./api.js";

const demoB64 = {
  ciphertext: "Y2lwaGVydGV4dC1kZW1v",
  content_hash: "Y29udGVudC1oYXNoLWRlbW8=",
  signature: "c2lnbmF0dXJlLWRlbW8=",
};

export default function App() {
  const [userId, setUserId] = useState("");
  const [conversationId, setConversationId] = useState("");
  const [messageId, setMessageId] = useState("");
  const [logs, setLogs] = useState([]);
  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [messageText, setMessageText] = useState("");
  const [error, setError] = useState("");

  const log = (msg) => setLogs((l) => [msg, ...l].slice(0, 8));
  const clearError = () => setError("");

  const createUser = async () => {
    clearError();
    try {
      const res = await apiPost("/users", {
        public_key: "pubkey-demo",
        fingerprint: "Y29udGVudC1oYXNoLWRlbW8=",
      });
      setUserId(res.user_id);
      log(`Usuario creado: ${res.user_id}`);
    } catch (e) {
      setError(String(e));
    }
  };

  const createConversation = async () => {
    clearError();
    try {
      const res = await apiPost("/conversations", {});
      setConversationId(res.conversation_id);
      log(`Conversacion: ${res.conversation_id}`);
    } catch (e) {
      setError(String(e));
    }
  };

  const addParticipant = async () => {
    clearError();
    try {
      await apiPost(`/conversations/${conversationId}/participants`, {
        user_id: userId,
      });
      log(`Participante agregado: ${userId}`);
    } catch (e) {
      setError(String(e));
    }
  };

  const loadConversations = async () => {
    clearError();
    try {
      const res = await apiGet(`/users/${userId}/conversations`);
      setConversations(res);
      log(`Conversaciones: ${res.length}`);
    } catch (e) {
      setError(String(e));
    }
  };

  const sendMessage = async () => {
    clearError();
    try {
      const payload = {
        sender_id: userId,
        ...demoB64,
        prev_hash: null,
        client_timestamp: new Date().toISOString(),
        key_id: "primary",
      };
      if (messageText.trim().length > 0) {
        payload.client_timestamp = new Date().toISOString();
      }
      const res = await apiPost(
        `/conversations/${conversationId}/messages`,
        payload
      );
      setMessageId(res.message_id);
      log(`Mensaje enviado: ${res.message_id}`);
    } catch (e) {
      setError(String(e));
    }
  };

  const listMessages = async () => {
    clearError();
    try {
      const res = await apiGet(`/conversations/${conversationId}/messages`, {
        limit: 50,
      });
      setMessages(res);
      log(`Mensajes: ${res.length}`);
    } catch (e) {
      setError(String(e));
    }
  };

  const markRead = async () => {
    clearError();
    try {
      await apiPost(`/messages/${messageId}/read`, { user_id: userId });
      log(`Leido: ${messageId}`);
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="page">
      <header className="hero">
        <div>
          <h1>Secure Vault</h1>
          <p>Cliente web minimo para probar el flujo E2EE.</p>
        </div>
        <div className="pill">
          API: {import.meta.env.VITE_API_URL || "http://localhost:8000"}
        </div>
      </header>

      <section className="card">
        <h2>1) Identidad</h2>
        <div className="row">
          <button onClick={createUser}>Crear usuario demo</button>
          <input
            placeholder="user_id"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
          />
          <button onClick={loadConversations}>Cargar conversaciones</button>
        </div>
        {error && <div className="error">Error: {error}</div>}
      </section>

      <section className="card">
        <h2>2) Conversacion</h2>
        <div className="row">
          <button onClick={createConversation}>Crear conversacion</button>
          <input
            placeholder="conversation_id"
            value={conversationId}
            onChange={(e) => setConversationId(e.target.value)}
          />
        </div>
        <div className="row">
          <button onClick={addParticipant}>Agregar participante</button>
        </div>
        <div className="row">
          {conversations.map((c) => (
            <button
              key={c.conversation_id}
              className="ghost"
              onClick={() => {
                setConversationId(c.conversation_id);
                log(`Seleccionada: ${c.conversation_id}`);
              }}
            >
              {c.conversation_id.slice(0, 8)}...
            </button>
          ))}
        </div>
      </section>

      <section className="card">
        <h2>3) Mensajes</h2>
        <div className="row">
          <button onClick={sendMessage}>Enviar mensaje demo</button>
          <input
            placeholder="message_id"
            value={messageId}
            onChange={(e) => setMessageId(e.target.value)}
          />
        </div>
        <div className="row">
          <input
            placeholder="mensaje (demo)"
            value={messageText}
            onChange={(e) => setMessageText(e.target.value)}
          />
        </div>
        <div className="row">
          <button onClick={listMessages}>Listar mensajes</button>
          <button onClick={markRead}>Marcar leido</button>
        </div>
        <pre className="code">{JSON.stringify(messages, null, 2)}</pre>
      </section>

      <section className="card">
        <h2>Logs</h2>
        <ul className="logs">
          {logs.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
