const path = require('path');
entryBase = './code/static/react/'

module.exports = {
  entry: "./code/static/react/app.jsx",
  output: {
    filename: 'main.js',
    path: path.resolve(__dirname, 'code/static'),
  },
  module: {
    rules : [
      {
        test: /\.m?jsx$/,
        exclude: /node_modules/,
        use: {
          loader: "babel-loader"
        }
      }
    ]
  }
};
