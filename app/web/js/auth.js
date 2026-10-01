import { api } from './api.js';
import { $ } from './util.js';
import { formModal } from './modal.js';

let instalando = false, alEntrar = () => {};

/* Muestra el ingreso, o el asistente de primer arranque si aún no hay usuarios. */
export async function mostrarLogin(alTerminar) {
  alEntrar = alTerminar;
  instalando = !(await api.get('/api/estado')).inicializado;
  $('#loginTitle').textContent = instalando ? 'Primer arranque' : 'Control de Procesos';
  $('#loginSub').textContent = instalando ? 'Cree la cuenta del administrador del sistema.' : 'Ingrese con su usuario y contraseña.';
  $('#lfNombre').style.display = $('#lfRepite').style.display = instalando ? '' : 'none';
  $('#loginBtn').textContent = instalando ? 'Crear administrador' : 'Ingresar';
  $('#l_password').value = $('#l_repite').value = ''; $('#loginErr').textContent = '';
  $('#login').classList.add('open');
  (instalando ? $('#l_nombre') : $('#l_usuario')).focus();
}

async function enviar(e) {
  e.preventDefault();
  const err = $('#loginErr'), usuario = $('#l_usuario').value.trim(), password = $('#l_password').value;
  err.textContent = '';
  try {
    if (instalando) {
      if (password.length < 8) { err.textContent = 'La contraseña debe tener al menos 8 caracteres.'; return; }
      if (password !== $('#l_repite').value) { err.textContent = 'Las contraseñas no coinciden.'; return; }
      await api.post('/api/instalacion', { usuario, nombre: $('#l_nombre').value.trim(), password }, true);
    } else {
      await api.post('/api/auth/login', { usuario, password }, true);
    }
  } catch (ex) { err.textContent = ex.message; return; }
  $('#l_password').value = $('#l_repite').value = '';
  $('#login').classList.remove('open');
  alEntrar();
}

export function cambiarPassword() {
  formModal({
    titulo: 'Cambiar mi contraseña',
    campos: [
      { k: 'actual', label: 'Contraseña actual', tipo: 'password' },
      { k: 'nueva', label: 'Nueva contraseña', tipo: 'password', hint: 'Mínimo 8 caracteres. Se cerrarán sus otras sesiones.' },
      { k: 'repite', label: 'Repita la nueva contraseña', tipo: 'password' },
    ],
    guardar: async v => {
      if (v.nueva !== v.repite) throw new Error('Las contraseñas no coinciden');
      await api.put('/api/me/password', { actual: v.actual, nueva: v.nueva });
    },
  });
}

export function iniciarAuth() { $('#loginForm').addEventListener('submit', enviar); }
