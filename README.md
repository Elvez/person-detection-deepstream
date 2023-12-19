#### Person detector (Nvidia Deepstream)
_Person detector complete pipeline for protocol-buffer input and protocol-buffer output. This pipeline uses redis end points for protocol-buffer transfer._

##### Building instructions
 * Build docker image,
    `docker image build -t person_detector:23.0.0_ds . `
 * Run the image with redis end points in env and runtime as nvidia,
   ```bash
   docker run --runtime=nvidia \
      --gpus=all \
      -eREDIS_HOST_PERSON_DETECTOR=<host> \
      -eREDIS_PORT_PERSON_DETECTOR=<port> \
      -eREDIS_DB_PERSON_DETECTOR=<db> \
      -eREDIS_OUTPUT_QUEUE_PERSON_DETECTOR=<output_queue> \
      -eREDIS_INPUT_QUEUE_PERSON_DETECTOR=<input_queue> \
      -d person_detector:23.0.0_ds
   ```

##### TODO
*Add aarch_64 build.*    