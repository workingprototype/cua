# C/UA Computer TypeScript Library

The TypeScript library for C/UA Computer - a powerful computer control and automation library.

## Overview

This library is a TypeScript port of the Python computer library, providing the same functionality for controlling virtual machines and computer interfaces. It includes:

- **Computer Class**: Main class for interacting with computers (virtual or host)
- **VM Providers**: Support for different VM providers (Lume, Lumier, Cloud)
- **Computer Interfaces**: OS-specific interfaces for controlling computers (macOS, Linux, Windows)
- **Utilities**: Helper functions for display parsing, memory parsing, logging, and telemetry

## Installation

```bash
npm install @cua/computer
# or
pnpm add @cua/computer
```

## Usage

```typescript
import { Computer } from '@cua/computer';

// Create a new computer instance
const computer = new Computer({
  display: '1024x768',
  memory: '8GB',
  cpu: '4',
  osType: 'macos',
  image: 'macos-sequoia-cua:latest'
});

// Start the computer
await computer.run();

// Get the computer interface for interaction
const interface = computer.interface;

// Take a screenshot
const screenshot = await interface.getScreenshot();

// Click at coordinates
await interface.click(500, 300);

// Type text
await interface.typeText('Hello, world!');

// Stop the computer
await computer.stop();
```

## Architecture

The library is organized into several key modules:

### Core Components
- `Computer`: Main class that manages VM lifecycle and interfaces
- `ComputerOptions`: Configuration options for computer instances

### Models
- `Display`: Display configuration (width, height)
- `ComputerConfig`: Internal computer configuration

### Providers
- `BaseVMProvider`: Abstract base class for VM providers
- `VMProviderFactory`: Factory for creating provider instances
- Provider types: `LUME`, `LUMIER`, `CLOUD`

### Interfaces
- `BaseComputerInterface`: Abstract base class for OS interfaces
- `InterfaceFactory`: Factory for creating OS-specific interfaces
- Interface models: Key types, mouse buttons, accessibility tree

### Utilities
- `Logger`: Logging with different verbosity levels
- `helpers`: Default computer management and sandboxed execution
- `utils`: Display/memory parsing, timeout utilities
- `telemetry`: Usage tracking and metrics

## Development

- Install dependencies:

```bash
pnpm install
```

- Run the unit tests:

```bash
pnpm test
```

- Build the library:

```bash
pnpm build
```

- Type checking:

```bash
pnpm typecheck
```

## External Dependencies

- `sharp`: For image processing and screenshot manipulation
- Additional provider-specific packages need to be installed separately:
  - `@cua/computer-lume`: For Lume provider support
  - `@cua/computer-lumier`: For Lumier provider support
  - `@cua/computer-cloud`: For Cloud provider support

## License

[MIT](./LICENSE) License 2025 [C/UA](https://github.com/trycua)
