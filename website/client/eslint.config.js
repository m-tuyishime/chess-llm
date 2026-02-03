import js from '@eslint/js';
import globals from 'globals';
import tseslint from 'typescript-eslint';
import prettierConfig from 'eslint-config-prettier';
import prettierPlugin from 'eslint-plugin-prettier';
import jsdoc from 'eslint-plugin-jsdoc';
import i18next from 'eslint-plugin-i18next';

export default tseslint.config(
  { ignores: ['dist'] },
  {
    extends: [
      js.configs.recommended,
      ...tseslint.configs.recommended,
      jsdoc.configs['flat/recommended-typescript'],
    ],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      prettier: prettierPlugin,
      jsdoc: jsdoc,
      i18next: i18next,
    },
    rules: {
      'prettier/prettier': 'error',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      'jsdoc/require-description': 'warn',
      'jsdoc/require-returns': 'off', // TypeScript handles return types
      'jsdoc/require-param-type': 'off', // TypeScript handles types
      'jsdoc/require-property-type': 'off', // TypeScript handles types
      'i18next/no-literal-string': [
        'warn',
        {
          markupOnly: true,
          ignoreAttribute: ['data-testid', 'className', 'style', 'key', 'role', 'type'],
        },
      ],
    },
  },
  prettierConfig
);
