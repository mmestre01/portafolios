# Felices 26, Gema

Minijuego web en Vite, TypeScript y Phaser 3 preparado para publicarse en `/felices26Gema/`.

## Desarrollo

```bash
npm install
npm run dev
npm run build
```

La configuración de Vite usa `base: "/felices26Gema/"`, por lo que los recursos se resuelven correctamente desde `https://mmestre.org/felices26Gema/`.

## Producción

El build queda en:

```text
felices26Gema/dist/
```

Para desplegarlo en la estructura actual de `mmestre.org`, copia o sincroniza el contenido de `felices26Gema/dist/` dentro de la carpeta servida como `/felices26Gema/` por Nginx. En este repositorio la configuración actual ya sirve archivos estáticos desde la raíz, así que también puedes publicar el `dist` como contenido final de esa subcarpeta.

Los assets reemplazables están documentados en `public/assets/README.md`.
