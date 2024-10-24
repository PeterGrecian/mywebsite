cvdev=dzicdevmyi
cv=4w46nd3x5l
apig=41bmi2t2yc

function terr() {
    pushd terraform
    terraform output
    popd
}

function tst() {
    timeout 5 curl -s $1 |& tee /tmp/out.txt | grep -q Oxford
    r=$?
    if [[ $r == 0 ]]; then
        echo -n "Yes "
    else
        echo -n "No  "
        cat /tmp/out.txt
        echo
    fi 
    echo "$r  $1"
}

function cxx() {
    echo $1 $2
    aws apigateway $2 --rest-api $3
}

function cmp() {
    cxx cv-dev $1 $cvdev
    cxx cv     $1 $cv
    echo
}

function hosts() {
    host www.petergrecian.co.uk
}

function tester() {

    tst https://w3.petergrecian.co.uk
    tst https://w3.petergrecian.co.uk/cv
    tst https://w3.petergrecian.co.uk/cvdev
    tst https://w3.petergrecian.co.uk/blah


}

function czz() {
    cmp get-authorizers
    cmp get-deployments
    cmp get-domain-names
    cmp get-resources
}

 