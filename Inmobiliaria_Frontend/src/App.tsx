import { useState } from "react";
import { LoginPage } from "./components/LoginPage";
import { PromptEditor } from "./components/PromptEditor";
import { getToken } from "./lib/api";

export default function App() {
  // Si hay token guardado, ya estamos logueados (no validamos al boot;
  // el primer GET fallará con 401 si está vencido, y volvemos al login).
  const [authed, setAuthed] = useState<boolean>(() => getToken() !== null);
  const [username, setUsername] = useState<string>("");

  if (!authed) {
    return (
      <LoginPage
        onLogin={(name) => {
          setUsername(name);
          setAuthed(true);
        }}
      />
    );
  }

  return (
    <PromptEditor
      username={username}
      onLogout={() => setAuthed(false)}
    />
  );
}
