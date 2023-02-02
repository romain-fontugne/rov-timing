
mkdir -p afrinic/
rsync -r rsync://rpki.afrinic.net/repository/member_repository/F362FC0B/97F3543019E311ECB7BBB859D8A014CE afrinic/

mkdir -p apnic/
rsync -r rsync://rpki.apnic.net/member_repository/A91A001E/35FA0F561D7811E293771FC408B02CD2 apnic/

mkdir -p arin/
rsync -r rsync://rpki.arin.net/repository/arin-rpki-ta/5e4a23ea-e80a-403e-b08c-2171da2157d3/521eb33f-9672-4cd9-acce-137227e971ac/f5a8e327-ebf4-4f4b-9073-90acd61797cc  arin/

mkdir -p lacnic/
rsync -r rsync://repository.lacnic.net/rpki/lacnic/5ecad2d5-c291-4a29-99f5-bfbe943581bc lacnic/
rsync -r rsync://repository.lacnic.net/rpki/lacnic/9ddc4dcd-fff1-4698-bc7c-be5edda4e615 lacnic/ 

mkdir -p ripe/
rsync -r rsync://rpki.ripe.net/repository/DEFAULT/eb/6f232e-2275-44e9-91c0-c7397a2669a9/1 ripe/
