pipeline {
  agent any
  stages {
    stage('Build') {
      steps {
        sh 'docker image build -t scenario-tool-interface .'
      }
    }
    stage('Test') {
      steps {
        sh '''set +e
docker run --name $UNIQUE_ID -e USERNAME="test@unit.com" -e PASSWORD=$PASSWORD -e USERNAME_GUEST="guest@unit.com" -e PASSWORD_GUEST=$PASSWORD_GUEST -e USERNAME_ADMIN="admin@danceplatform.org" -e PASSWORD_ADMIN=$PASSWORD_ADMIN  scenario-tool-interface
set -e'''
        sh '''docker cp $UNIQUE_ID:/tmp/test.xml .
docker rm -f $UNIQUE_ID'''
        junit 'test.xml'
      }
    }
    stage('Deploy') {
            when {
            expression { tag "v-*" && (currentBuild.result == null || currentBuild.result == 'SUCCESS' )}
             }
            steps {
                echo 'Deploy to pypy'
                sh 'make deploy'
                sh 'python setup.py sdist'
                sh 'twine upload dist/* -u $USERNAME_PYPI -p $PASSWORD_PYPI'
            }
        }
  }
  environment {
    PASSWORD = credentials('test@unit.com')
    PASSWORD_GUEST = credentials('guest@unit.com')
    PASSWORD_ADMIN = credentials('admin@danceplatform.org')
    USERNAME_PYPI = credentials('pypi_user')
    PASSWORD_PYPI = credentials('pypi_pass')
    UNIQUE_ID = UUID.randomUUID().toString()
  }
}