// Tailwind 4 + HeroUI. Loaded through craco's `style.postcss.mode: 'file'` so CRA's postcss-preset-env can't rewrite @layer.
module.exports = {
  plugins: {
    '@tailwindcss/postcss': {},
    autoprefixer: {},
  },
}
