FROM  jhginn/devcontainer:ubuntu2204-pyuv312-latest-gcloud

ENV RUFF_CACHE_DIR=$HOME/workspace/.cache/ruff
ENV PRE_COMMIT_HOME=$HOME/workspace/.cache/pre-commit
ENV NVM_DIR="$HOME/.nvm"
ARG NODE_VERSION="20"
ENV PATH="${NVM_DIR}/versions/node/v${NODE_VERSION}/bin:${PATH}"

RUN pipx install --force uv==0.9.7

USER vscode
WORKDIR /home/vscode

ENV NVM_DIR="/home/vscode/.nvm"
RUN touch /home/vscode/.bashrc

RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash \
    && . "$NVM_DIR/nvm.sh" \
    && nvm install ${NODE_VERSION} \
    && nvm alias default ${NODE_VERSION} \
    && nvm use default \
    && npm install -g @google/gemini-cli

RUN echo '\nexport NVM_DIR="/home/vscode/.nvm"' >> /home/vscode/.bashrc && \
    echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm' >> /home/vscode/.bashrc && \
    echo '[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion' >> /home/vscode/.bashrc

ENV PATH="/home/vscode/.nvm/versions/node/v${NODE_VERSION}/bin:${PATH}"
