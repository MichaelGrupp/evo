To install Jupyter, call:
```
pip install jupyter
jupyter nbextension enable --py --sys-prefix widgetsnbextension
```

### Local Jupyter notebook access

Go to the `evo` source folder in a terminal and run: `jupyter notebook` (starts server and opens browser window with notebook).

### Remote Jupyter notebook access

Notebook servers can also be accessed via the browser of a remote PC on the local network without installing Jupyter.

**Do once:**

* disable tokens on your **server** side:
  * `jupyter notebook --generate-config`
  * go to the generated config file, uncomment and change the `c.NotebookApp.token` parameter to an empty string
  * **TODO**: enable password authentication without annoying tokens

**Anytime you want to start a server:**

* start the notebook on the **server**: `jupyter notebook --no-browser --port=8888`
* access notebook on **remote** PC:
  * establish SSH forwarding: `ssh username@remotehost -L 8889:localhost:8888`
  * this forwards remote 8888 port to local 8889 (numbers are just examples)
  * open the notebook in a browser: `localhost:8889`