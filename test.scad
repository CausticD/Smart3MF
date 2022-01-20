sub_model = "All"; // [All,Hook,Cube1,Cube2]

hole_size = 25/2;
center_size = 35/2;
arm_length = 50;
arm_width = 14;
main_height = 5;
hook_height = 4;
hook_length = 4;

clip_size = 200;

$fn = 100;

if(sub_model=="All" || sub_model=="Hook")
{
    intersection()
    {
        translate([0,clip_size/2,0]) cube([clip_size, clip_size, clip_size], center = true);

        difference()
        {
            union()
            {
                translate([0,0,main_height/2]) {
                    cylinder(main_height, center_size, center_size, center = true);
                    cube([arm_length, arm_width, main_height], center = true);
                }

                translate([0,0,main_height+hook_height/2]) {
                    offset = arm_length/2 - hook_length/2;
                    translate([-offset,0,0]) cube([hook_length, arm_width, hook_height], center = true);
                    translate([+offset,0,0]) cube([hook_length, arm_width, hook_height], center = true);
                }
            }

            translate([0,0,main_height/2]) cylinder(main_height+1, hole_size, hole_size, center = true);
        }
    }
}

if(sub_model=="All" || sub_model=="Cube1")
{
    cube([5, 5, 5], center = true);
}

if(sub_model=="All" || sub_model=="Cube2")
{
    cube([15, 2, 2], center = true);
}