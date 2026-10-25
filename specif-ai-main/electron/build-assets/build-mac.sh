export CSC_LINK="$(pwd)/build-assets/applep12devcert.p12"
export CSC_KEY_PASSWORD=""

npm run package:mac && npm run package:win

