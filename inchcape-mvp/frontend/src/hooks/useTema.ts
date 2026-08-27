import { useEffect, useState } from 'react';

export type Tema = 'light' | 'dark' | null; // null = sigue la preferencia del sistema

const CLAVE = 'tema';

function leerGuardado(): Tema {
  const v = localStorage.getItem(CLAVE);
  return v === 'light' || v === 'dark' ? v : null;
}

/** Maneja el atributo data-theme en <html> -- el CSS ya sabe reaccionar a
 * eso (ver index.css): sin atributo sigue prefers-color-scheme, con
 * atributo el valor manual gana siempre. */
export function useTema() {
  const [tema, setTema] = useState<Tema>(leerGuardado);

  useEffect(() => {
    if (tema) {
      document.documentElement.setAttribute('data-theme', tema);
      localStorage.setItem(CLAVE, tema);
    } else {
      document.documentElement.removeAttribute('data-theme');
      localStorage.removeItem(CLAVE);
    }
  }, [tema]);

  return { tema, setTema };
}
