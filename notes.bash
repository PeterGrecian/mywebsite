cvdev=dzicdevmyi
cv=4w46nd3x5l
function tst() {
    curl -s $1 |& tee /tmp/out.txt | grep -q Oxford
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


function compare() {
tst https://$cvdev.execute-api.eu-west-1.amazonaws.com/dev/cv-dev
tst https://$cv.execute-api.eu-west-1.amazonaws.com/default/cv
#aws apigateway get-autorizers --rest-api
}

function czz() {
    cmp get-authorizers
    cmp get-deployments
    cmp get-domain-names
    cmp get-resources
}

 