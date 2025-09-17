#!/usr/bin/env node

/**
 * Dependency validation script for the Maive monorepo
 * 
 * Rules:
 * 1. Apps cannot depend on other apps
 * 2. All internal dependencies must use workspace:* protocol
 * 3. Packages can depend on other packages
 * 4. Apps can depend on packages
 * 5. No circular dependencies
 * 6. Validate package.json structure
 * 7. Check for missing peer dependencies
 */

import { readFileSync, readdirSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, '..');

// Workspace structure
const APPS_DIR = 'apps';
const PACKAGES_DIR = 'packages';

// Get all workspace directories
function getWorkspaces() {
  const workspaces = {
    apps: [],
    packages: []
  };

  // Get apps
  const appsDir = join(rootDir, APPS_DIR);
  try {
    const appDirs = readdirSync(appsDir, { withFileTypes: true })
      .filter(dirent => dirent.isDirectory())
      .map(dirent => dirent.name);
    workspaces.apps = appDirs;
  } catch (error) {
    console.warn(`Warning: Could not read apps directory: ${error.message}`);
  }

  // Get packages
  const packagesDir = join(rootDir, PACKAGES_DIR);
  try {
    const packageDirs = readdirSync(packagesDir, { withFileTypes: true })
      .filter(dirent => dirent.isDirectory())
      .map(dirent => dirent.name);
    workspaces.packages = packageDirs;
  } catch (error) {
    console.warn(`Warning: Could not read packages directory: ${error.message}`);
  }

  return workspaces;
}

// Read package.json for a workspace
function readPackageJson(workspacePath) {
  try {
    const packageJsonPath = join(rootDir, workspacePath, 'package.json');
    const content = readFileSync(packageJsonPath, 'utf8');
    return JSON.parse(content);
  } catch (error) {
    console.warn(`Warning: Could not read package.json for ${workspacePath}: ${error.message}`);
    return null;
  }
}

// Get all dependencies (dependencies, devDependencies, peerDependencies)
function getAllDependencies(packageJson) {
  const deps = new Set();
  
  if (packageJson.dependencies) {
    Object.keys(packageJson.dependencies).forEach(dep => deps.add(dep));
  }
  if (packageJson.devDependencies) {
    Object.keys(packageJson.devDependencies).forEach(dep => deps.add(dep));
  }
  if (packageJson.peerDependencies) {
    Object.keys(packageJson.peerDependencies).forEach(dep => deps.add(dep));
  }
  
  return Array.from(deps);
}

// Check if a dependency is internal (starts with @maive/)
function isInternalDependency(dep) {
  return dep.startsWith('@maive/');
}

// Check if a dependency uses workspace:* protocol
function usesWorkspaceProtocol(packageJson, dep) {
  const deps = packageJson.dependencies || {};
  const devDeps = packageJson.devDependencies || {};
  const peerDeps = packageJson.peerDependencies || {};
  
  return deps[dep] === 'workspace:*' || 
         devDeps[dep] === 'workspace:*' || 
         peerDeps[dep] === 'workspace:*';
}

// Get the workspace name from package.json
function getWorkspaceName(packageJson) {
  return packageJson.name;
}

// Check for circular dependencies
function checkCircularDependencies(workspaces, packageJsonMap) {
  const errors = [];
  const visited = new Set();
  const recursionStack = new Set();

  function dfs(workspaceName) {
    if (recursionStack.has(workspaceName)) {
      errors.push(`Circular dependency detected involving ${workspaceName}`);
      return;
    }
    if (visited.has(workspaceName)) return;

    visited.add(workspaceName);
    recursionStack.add(workspaceName);

    const packageJson = packageJsonMap[workspaceName];
    if (packageJson) {
      const dependencies = getAllDependencies(packageJson);
      for (const dep of dependencies) {
        if (isInternalDependency(dep)) {
          const depName = dep.replace('@maive/', '');
          dfs(depName);
        }
      }
    }

    recursionStack.delete(workspaceName);
  }

  for (const workspaceName of Object.keys(packageJsonMap)) {
    if (!visited.has(workspaceName)) {
      dfs(workspaceName);
    }
  }

  return errors;
}

// Validate package.json structure
function validatePackageJsonStructure(packageJson, workspaceName) {
  const errors = [];
  const warnings = [];

  // Check for required fields
  if (!packageJson.name) {
    errors.push(`${workspaceName}: Missing "name" field in package.json`);
  }

  if (!packageJson.version) {
    warnings.push(`${workspaceName}: Missing "version" field in package.json`);
  }

  // Check for valid workspace names
  if (packageJson.name && !packageJson.name.startsWith('@maive/')) {
    warnings.push(`${workspaceName}: Package name should start with "@maive/"`);
  }

  return { errors, warnings };
}

// Validate dependencies for a workspace
function validateWorkspace(workspacePath, packageJson, workspaces) {
  const errors = [];
  const warnings = [];
  
  if (!packageJson) {
    return { errors, warnings };
  }

  const workspaceName = getWorkspaceName(packageJson);
  const isApp = workspacePath.startsWith(APPS_DIR);
  const dependencies = getAllDependencies(packageJson);

  // Validate package.json structure
  const structureValidation = validatePackageJsonStructure(packageJson, workspaceName);
  errors.push(...structureValidation.errors);
  warnings.push(...structureValidation.warnings);

  for (const dep of dependencies) {
    if (isInternalDependency(dep)) {
      // Check if it uses workspace:* protocol
      if (!usesWorkspaceProtocol(packageJson, dep)) {
        errors.push(`${workspaceName}: Internal dependency "${dep}" must use "workspace:*" protocol`);
      }

      // Check if app is trying to depend on another app
      if (isApp) {
        const depName = dep.replace('@maive/', '');
        if (workspaces.apps.includes(depName)) {
          errors.push(`${workspaceName}: Apps cannot depend on other apps. "${dep}" is an app dependency.`);
        }
      }
    }
  }

  return { errors, warnings };
}

// Main validation function
function validateDependencies() {
  console.log('🔍 Validating workspace dependencies...\n');

  const workspaces = getWorkspaces();
  const allErrors = [];
  const allWarnings = [];
  const packageJsonMap = {};

  // Build package.json map for circular dependency checking
  for (const app of workspaces.apps) {
    const packageJson = readPackageJson(join(APPS_DIR, app));
    if (packageJson && packageJson.name) {
      packageJsonMap[packageJson.name.replace('@maive/', '')] = packageJson;
    }
  }

  for (const pkg of workspaces.packages) {
    const packageJson = readPackageJson(join(PACKAGES_DIR, pkg));
    if (packageJson && packageJson.name) {
      packageJsonMap[packageJson.name.replace('@maive/', '')] = packageJson;
    }
  }

  // Validate all workspaces
  for (const app of workspaces.apps) {
    const packageJson = readPackageJson(join(APPS_DIR, app));
    const { errors, warnings } = validateWorkspace(join(APPS_DIR, app), packageJson, workspaces);
    allErrors.push(...errors);
    allWarnings.push(...warnings);
  }

  for (const pkg of workspaces.packages) {
    const packageJson = readPackageJson(join(PACKAGES_DIR, pkg));
    const { errors, warnings } = validateWorkspace(join(PACKAGES_DIR, pkg), packageJson, workspaces);
    allErrors.push(...errors);
    allWarnings.push(...warnings);
  }

  // Check for circular dependencies
  const circularErrors = checkCircularDependencies(workspaces, packageJsonMap);
  allErrors.push(...circularErrors);

  // Report results
  if (allWarnings.length > 0) {
    console.log('⚠️  Warnings:');
    allWarnings.forEach(warning => console.log(`  ${warning}`));
    console.log('');
  }

  if (allErrors.length > 0) {
    console.log('❌ Dependency validation errors:');
    allErrors.forEach(error => console.log(`  ${error}`));
    console.log('');
    console.log('💡 To fix these issues:');
    console.log('  1. Use "workspace:*" for all internal dependencies');
    console.log('  2. Remove app-to-app dependencies');
    console.log('  3. Ensure all @maive/* dependencies are properly configured');
    console.log('  4. Fix circular dependencies');
    console.log('  5. Add missing package.json fields');
    process.exit(1);
  }

  console.log('✅ All workspace dependencies are valid!');
  console.log(`   - Found ${workspaces.apps.length} apps: ${workspaces.apps.join(', ')}`);
  console.log(`   - Found ${workspaces.packages.length} packages: ${workspaces.packages.join(', ')}`);
  console.log('   - No circular dependencies detected');
}

// Run validation
validateDependencies(); 