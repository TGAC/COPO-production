
while read -r line
do
IFS=' ' read -ra ADDR <<< "$line"
biosampleAccession=${ADDR[0]}
long=${ADDR[1]}
lat=${ADDR[2]}

output=$(curl -s -X POST -H 'Content-Type: application/x-www-form-urlencoded' -d "result=sample&query=accession=${biosampleAccession}&fields=secondary_sample_accession&format=tsv" 'https://www.ebi.ac.uk/ena/portal/api/search')
  sraAccession=`echo $output | sed 's/.*\ERS\(.*\)$/\1/'`
  echo "{"
  echo '"sample_accession": "'ERS$sraAccession'",'
  echo '"geographic location (latitude)" : "'$long'",'
  echo '"geographic location (longitude)" : "'$lat'",'
  echo "}," 
done < /Downloads/data_to_be_updated.txt
