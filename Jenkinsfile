pipeline {
    agent {
        label 'master'
    }
    triggers {
        upstream(upstreamProjects: '../Reference/ref_alcohol',
                 threshold: hudson.model.Result.SUCCESS)
    }
    stages {
        stage('Clean') {
            steps {
                sh 'rm -rf out'
            }
        }
        stage('Transform') {
            agent {
                docker {
                    image 'cloudfluff/databaker'
                    reuseNode true
                }
            }
            steps {
                script {
                    for (def file : findFiles(glob: '*.ipynb')) {
                        sh "jupyter-nbconvert --output-dir=out --ExecutePreprocessor.timeout=None --execute '${file.name}'"
                    }
                }
            }
        }
        stage('Review') {
            steps {
                error "Needs review"
            }
        }
    }
    post {
        always {
            script {
                archiveArtifacts 'out/*'
                updateCard '5b4f3c98336dc1d9d4346c17'
            }
        }
        success {
            build job: '../GDP-tests', wait: false
        }
    }
}
