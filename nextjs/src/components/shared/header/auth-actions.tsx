import Link from "next/link";


export default function AuthActions() {
  return (
    <div className="auth__actions">
      <Link className="btn-main" href="/login">Login</Link>
      <Link className="btn-line" href="/register">Register</Link>
    </div>
  );
}
