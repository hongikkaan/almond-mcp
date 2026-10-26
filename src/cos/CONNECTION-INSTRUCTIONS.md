Initialization only advertises tools; it does not start Rhino or a modeling worker. To open a separate Rhino for a saved .3dm, explicitly call start_session with a unique request_id. Reuse that request_id to check a delayed start; never automatically repeat it with a new ID. Otherwise list and connect an advertised Rhino.

Select a Rhino by the verified model_filename and model_path in list_connections. Connect with the exact host_id and model_path shown there; confirm the same file in the connect result. In-use or unavailable entries may have no verified filename.

Use the explicit connection_id from connect for every call. Document changes require disconnect/reconnect. A timeout is not a rollback; inspect Rhino before repeating a mutation.
