import { mergeConfig } from "vitest/config";
import viteConfig from "./vite.config";
import { defineConfig } from "vitest/config";

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: ["./src/test-setup.ts"],
      coverage: {
        provider: "v8",
        reporter: ["text", "lcov", "html"],
        thresholds: {
          branches: 80,
          lines: 80,
        },
        exclude: [
          "node_modules/",
          "dist/**",
          "src/test-setup.ts",
          "src/main.tsx",
          "src/App.tsx",
          "src/router.tsx",
          "src/pages/**",
          "src/layouts/**",
          "src/components/layout/**",
          "**/*.d.ts",
          "vite.config.ts",
          "vitest.config.ts",
          "eslint.config.js",
        ],
      },
    },
  }),
);
