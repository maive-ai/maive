# Maive Brand Package Guide

This guide explains how to use the `@maive/brand` package to maintain consistent branding across your applications.

## Quick Start

### 1. Add Your Brand Assets

Place your brand assets in the appropriate directories:

```
packages/brand/
├── logos/
│   ├── logo.svg          # Main logo
│   ├── favicon.png       # Favicon
│   ├── logo-white.svg    # Logo for dark backgrounds
│   └── logo-black.svg    # Logo for light backgrounds
├── fonts/
│   ├── inter.woff2       # Inter font family
│   └── jetbrains-mono.woff2  # JetBrains Mono font
└── tailwind/
    └── theme.ts          # Brand theme configuration
```

### 2. Update Your Brand Colors

Edit `packages/brand/tailwind/theme.ts` and replace the placeholder colors with your actual brand colors:

```typescript
export const brandColors: BrandColors = {
  primary: {
    50: '#your-primary-50',
    100: '#your-primary-100',
    // ... continue for all shades
    950: '#your-primary-950',
  },
  // ... update secondary, accent, and neutral colors
};
```

### 3. Build the Brand Package

```bash
pnpm --filter=@maive/brand build
```

### 4. Use in Your Applications

#### In Web Apps

```typescript
// Import brand assets
import logo from '@maive/brand/logos/logo.svg';
import { brandTheme } from '@maive/brand/tailwind';

// Use in components
function Header() {
  return (
    <header className="bg-brand-primary text-white">
      <img src={logo} alt="Maive" className="h-8" />
    </header>
  );
}
```

#### In Tailwind Config

```typescript
import { brandTheme } from '@maive/brand/tailwind';

export default {
  theme: {
    extend: brandTheme,
  },
};
```

## Brand Color Usage

### CSS Custom Properties

The brand package provides CSS custom properties for all brand colors:

```css
/* Primary colors */
--color-primary-50: #f0f9ff;
--color-primary-100: #e0f2fe;
/* ... etc */

/* Secondary colors */
--color-secondary-50: #f8fafc;
/* ... etc */

/* Accent colors */
--color-accent-50: #fdf4ff;
/* ... etc */

/* Neutral colors */
--color-neutral-50: #fafafa;
/* ... etc */
```

### Tailwind Classes

Use Tailwind classes with your brand colors:

```html
<!-- Background colors -->
<div class="bg-primary-500">Primary background</div>
<div class="bg-secondary-200">Secondary background</div>
<div class="bg-accent-300">Accent background</div>

<!-- Text colors -->
<h1 class="text-primary-700">Primary text</h1>
<p class="text-secondary-600">Secondary text</p>

<!-- Border colors -->
<button class="border border-primary-500">Primary border</button>
```

### Utility Classes

The brand package also provides semantic utility classes:

```html
<div class="bg-brand-primary">Brand primary background</div>
<div class="text-brand-secondary">Brand secondary text</div>
<div class="border-brand-accent">Brand accent border</div>
```

## Typography

### Font Families

The brand package includes:

- **Inter** - Primary sans-serif font
- **JetBrains Mono** - Monospace font for code
- **Display font** - For headings (currently set to Inter)

### Usage

```html
<h1 class="font-display text-4xl">Display heading</h1>
<p class="font-sans">Body text with Inter</p>
<code class="font-mono">Code with JetBrains Mono</code>
```

## Spacing and Layout

### Custom Spacing Scale

The brand package includes a custom spacing scale:

```html
<div class="p-xs">Extra small padding (4px)</div>
<div class="p-sm">Small padding (8px)</div>
<div class="p-md">Medium padding (16px)</div>
<div class="p-lg">Large padding (24px)</div>
<div class="p-xl">Extra large padding (32px)</div>
```

### Border Radius

```html
<div class="rounded-sm">Small radius (2px)</div>
<div class="rounded-md">Medium radius (6px)</div>
<div class="rounded-lg">Large radius (8px)</div>
<div class="rounded-xl">Extra large radius (12px)</div>
```

## Animations

### Brand Animations

```html
<div class="animate-fade-in">Fade in animation</div>
<div class="animate-slide-up">Slide up animation</div>
<div class="animate-scale-in">Scale in animation</div>
<div class="animate-bounce-subtle">Subtle bounce</div>
```

## Best Practices

### 1. Color Usage

- Use primary colors for main actions and branding
- Use secondary colors for supporting elements
- Use accent colors sparingly for highlights
- Use neutral colors for text and backgrounds

### 2. Typography

- Use Inter for all body text and UI elements
- Use JetBrains Mono only for code snippets
- Maintain consistent font sizes using the provided scale

### 3. Spacing

- Use the provided spacing scale for consistent layouts
- Prefer the semantic spacing classes (xs, sm, md, lg, xl)

### 4. Accessibility

- Ensure sufficient color contrast between text and backgrounds
- Use semantic color combinations (e.g., primary-500 on white)
- Test with color blindness simulators

## Development Workflow

### 1. Making Changes

1. Update `packages/brand/tailwind/theme.ts` with your changes
2. Add new assets to the appropriate directories
3. Run `pnpm --filter=@maive/brand build`
4. Test your changes in consuming applications

### 2. Adding New Assets

1. Place new assets in the appropriate directory
2. Update the build scripts if needed
3. Rebuild the package
4. Update documentation

### 3. Version Control

- Commit brand assets to version control
- Use semantic versioning for the brand package
- Document breaking changes in the changelog

## Troubleshooting

### Build Issues

If you encounter build issues:

1. Ensure all dependencies are installed: `pnpm install`
2. Clean and rebuild: `pnpm --filter=@maive/brand clean && pnpm --filter=@maive/brand build`
3. Check TypeScript compilation: `pnpm --filter=@maive/brand typecheck`

### Import Issues

If imports aren't working:

1. Ensure the brand package is listed as a dependency
2. Rebuild the brand package
3. Restart your development server

### CSS Issues

If CSS variables aren't loading:

1. Ensure the brand CSS is imported in your main CSS file
2. Check that the build process completed successfully
3. Verify the CSS file path is correct

## Examples

### Complete Component Example

```tsx
import logo from '@maive/brand/logos/logo.svg';

export function BrandHeader() {
  return (
    <header className="bg-primary-500 text-white p-md">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-md">
          <img src={logo} alt="Maive" className="h-8" />
          <h1 className="text-xl font-display">Maive</h1>
        </div>
        <nav className="flex space-x-lg">
          <a href="#" className="hover:text-primary-200 transition-colors">
            Dashboard
          </a>
          <a href="#" className="hover:text-primary-200 transition-colors">
            Settings
          </a>
        </nav>
      </div>
    </header>
  );
}
```

### Button Component with Brand Colors

```tsx
import { Button } from '@maive/ui';

export function BrandButton({ variant = 'primary', children, ...props }) {
  const variants = {
    primary: 'bg-primary-500 hover:bg-primary-600 text-white',
    secondary: 'bg-secondary-500 hover:bg-secondary-600 text-white',
    accent: 'bg-accent-500 hover:bg-accent-600 text-white',
    outline: 'border border-primary-500 text-primary-500 hover:bg-primary-50',
  };

  return (
    <Button className={`${variants[variant]} transition-colors`} {...props}>
      {children}
    </Button>
  );
}
```
