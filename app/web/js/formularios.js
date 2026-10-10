/* Punto único de entrada a los dos formularios grandes. Están partidos en proc.js y act.js porque
   con los campos de la v2 pasan de 600 líneas entre los dos. */
import { iniciarProc, openProc } from './proc.js';
import { iniciarAct, openAct, openAudiencia, crearSiguiente } from './act.js';

export { openProc, openAct, openAudiencia, crearSiguiente };

export function iniciarFormularios() {
  iniciarProc();
  iniciarAct();
}
