# Registry App (registry-app)

Signal Registry, Registry Server

## Dependencies

- Node.js (v24): JavaScript runtime built on Chrome's V8 JavaScript engine.

```
# Download and install nvm:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash

# in lieu of restarting the shell
\. "$HOME/.nvm/nvm.sh"

# Download and install Node.js:
nvm install 24

# Verify the Node.js version:
node -v # Should print "v24.16.0".

# Verify npm version:
npm -v # Should print "11.13.0".

```

- Quasar CLI: Command-line interface for Quasar Framework

```
# Install Quasar CLI globally:
npm install -g @quasar/cli
```

## Initialization

```
# Iinitialize the project using Quasar CLI:
# Be aware that this command will overwrite existing files in the current directory.
# Thus keep a backup of your important files before running this command.

npm init quasar@latest .

# Add electron mode to the project:
# If Electron download failed do the following:
# - Manually add release files to the project into `node_modules/electron/dist`
# - Add `path.txt` file into `node_modules/electron/dist` with the just only 'electron' text content

quasar mode add electron

# Install the dependencies for electron mode:
npm install -D @electron/remote

```

## Install the Dependencies

```bash
npm install
```

## Start the App in Development Mode

```bash
# Webpage mode
npm run dev

# Electron mode
npm run dev:electron
```

### Lint the files

```bash
npm run lint
```

### Format the files

```bash
npm run format
```

### Build the app for production

```bash
quasar build
```

### Customize the configuration

See [Configuring quasar.config.js](https://v2.quasar.dev/quasar-cli-vite/quasar-config-js).


## Build

```bash

# HTML mode
npm run build

# Electron mode
# If executable file is not generated, do the following:
# - Manually change electron.bundler to 'builder' in `quasar.config.js` file
npm run build:electron

```