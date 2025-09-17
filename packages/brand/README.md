# @maive/brand

Brand assets and theme configuration for the Maive application.

## Structure

```
packages/brand/
├── logos/          # Logo assets (SVG, PNG, etc.)
├── fonts/          # Font files (WOFF2, etc.)
├── tailwind/       # Tailwind theme configuration
│   └── theme.ts    # Main theme file
└── package.json
```

## Usage

### In Tailwind Config

```typescript
import type { Config } from 'tailwindcss';
import { brandTheme } from '@maive/brand/tailwind';

export default {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: brandTheme,
  },
  plugins: [],
} satisfies Config;
```

### Direct Imports

```typescript
import { colors, fonts, spacing } from '@maive/brand/tailwind';

// Use in your components
const myColors = colors.primary;
```

### Asset Imports (via Vite aliases)

```typescript
// In your components
import logo from '@brand/logos/logo.svg';
import interFont from '@brand/fonts/inter.woff2';
```

## Development

### Adding Brand Colors

Edit `tailwind/theme.ts` to update your brand colors:

```typescript
export const brandColors: BrandColors = {
  primary: {
    50: '#f0f9ff',
    100: '#e0f2fe',
    // ... add your brand colors
    500: '#0ea5e9', // Your main brand color
    950: '#082f49',
  },
  // ... other color palettes
};
```

### Adding Assets

1. **Logos**: Place logo files in `logos/` directory
2. **Fonts**: Place font files in `fonts/` directory

### Building

```bash
# Build TypeScript theme
pnpm --filter=@maive/brand build

# Or just typecheck
pnpm --filter=@maive/brand typecheck
```

## Vite Integration

The web app is configured with Vite aliases for easy asset access:

- `@brand` → `packages/brand`
- `@brand/logos` → `packages/brand/logos`
- `@brand/fonts` → `packages/brand/fonts`

This allows direct imports without build scripts.
